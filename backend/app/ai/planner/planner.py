"""
Planner Service — Milestone 10 / Production Readiness

The PlannerService is the ONLY component that produces ExecutionPlans.

Architecture contract:
  - Input:  PlannerRequest (internal only, never from the client)
  - Output: ExecutionPlan (validated Pydantic model)
  - Errors: NEVER propagate. Always return a safe fallback ExecutionPlan.
  - Retrieval: NEVER performed here.
  - Tool invocation: NEVER performed here.
  - Final answers: NEVER generated here.

Flow:
  1. Try heuristic fast-path (greetings, intent classification, no-doc queries).
  2. Call LLM with the system prompt + user context.
  3. Strip markdown fences and parse JSON.
  4. Validate against ExecutionPlan Pydantic model.
  5. If validation fails → retry once with a stricter prompt hint.
  6. If retry fails → return a safe GENERAL fallback plan.
  7. If has_documents=False → short-circuit to GeneralLLM plan before LLM call.

Observability:
  - All decisions are logged with pipeline_id / conversation_id context.
  - Retry reasons and fallback triggers are logged as warnings.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Optional

from app.ai.config import ai_config
from app.ai.llm.manager import DynamicLLMProvider
from app.ai.planner.prompt import build_planner_prompt
from app.ai.planner.schemas import (
    ExecutionPlan,
    ExecutionStep,
    PlannerRequest,
    ResponseMode,
    TaskType,
    ToolName,
)

logger = logging.getLogger(__name__)

PLANNER_VERSION = "2.1.0"

_GREETING_TOKENS = frozenset({
    "hi", "hello", "hey", "thanks", "thank", "thank you", "ok", "okay", "bye",
    "goodbye", "good morning", "good afternoon", "good evening", "great",
    "cool", "nice", "sure", "yep", "nope", "yes", "no", "welcome", "cheers",
})

# Explicit world-knowledge cues that should NOT use document tools.
_GENERAL_KNOWLEDGE_PATTERNS = [
    r"\bcapital of\b",
    r"\bwho (is|was) the (president|prime minister|ceo)\b",
    r"\bwhat (is|are) the (speed of light|population of)\b",
    r"\bhow (many|tall|long|old) (is|are|was|were)\b.+\b(earth|moon|sun|universe)\b",
]

_MEMORY_PATTERNS = [
    r"\bwhat did you (say|tell|mention|mean)\b",
    r"\b(earlier|previously|before|last time)\b",
    r"\b(remind me|you said|you mentioned|our conversation)\b",
    r"\bwhat (was|were) (my|your) (last|previous)\b",
]

_FOLLOWUP_PATTERNS = [
    r"^(explain|expand|elaborate) (that|this|it|further|more)\b",
    r"^(tell me more|go on|continue|and then)\b",
    r"^(why|how so|can you clarify)\b",
]

_COMPARE_PATTERNS = [
    r"\b(compare|contrast|versus|vs\.?|difference between|differences between)\b",
    r"\bhow (do|does|does) .+ differ\b",
]

_TRANSFORM_PATTERNS = [
    r"\b(summarize|summarise|summary of|give me a summary)\b",
    r"\b(rewrite|rephrase|paraphrase)\b",
    r"\b(improve|polish|edit|make .+ (more )?professional)\b",
    r"\b(translate|translation)\b",
    r"\bexplain (this|the|my) (document|file|pdf|synopsis|chapter|introduction|section)\b",
    r"\bwhat is (this|the|my) (document|file|pdf|synopsis) about\b",
    r"\brewrite the (introduction|intro|conclusion|abstract)\b",
]

_REWRITE_PATTERNS = [
    r"\b(rewrite|rephrase|paraphrase|improve|polish)\b",
]

_FACT_LOOKUP_PATTERNS = [
    r"^(what is|what's|who is|who's|who wrote|when was|where (is|did|was)|how (does|did|do|is|are))\b",
    r"^(find|search for|locate|look up)\b",
    r"\b(in (the|my|this) (document|file|pdf|synopsis))\b",
]


def _is_greeting(query: str) -> bool:
    """Return True for trivial conversational messages."""
    q = query.strip().lower().rstrip("!.,?")
    if not q:
        return True
    if q in _GREETING_TOKENS:
        return True
    # Short phrases composed entirely of greeting tokens (e.g. "ok cool")
    parts = [p for p in re.split(r"\s+", q) if p]
    if 1 < len(parts) <= 3 and all(p.rstrip("!.,?") in _GREETING_TOKENS for p in parts):
        return True
    return False


def _has_any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _reader_plan(task: TaskType, reason: str, num_documents: int) -> ExecutionPlan:
    desc = (
        "Read multiple documents for comparison/transformation."
        if num_documents > 1 and task == TaskType.DOCUMENT_COMPARISON
        else "Read full document for transformation."
    )
    return ExecutionPlan(
        task=task,
        reasoning=reason,
        confidence=1.0,
        steps=[ExecutionStep(tool=ToolName.DOCUMENT_READER, description=desc)],
        requires_documents=True,
        requires_retrieval=False,
        requires_history=False,
        requires_general_knowledge=False,
        response_mode=ResponseMode.STREAM,
        max_chunks=ai_config.MAX_CHUNKS,
        planner_version=PLANNER_VERSION,
    )


def _search_plan(reason: str, query: str) -> ExecutionPlan:
    return ExecutionPlan(
        task=TaskType.DOCUMENT_QA,
        reasoning=reason,
        confidence=1.0,
        steps=[ExecutionStep(tool=ToolName.DOCUMENT_SEARCH, description="Search documents for facts.")],
        rewritten_query=query,
        requires_documents=True,
        requires_retrieval=True,
        requires_history=False,
        requires_general_knowledge=False,
        response_mode=ResponseMode.STREAM,
        max_chunks=ai_config.MAX_CHUNKS,
        planner_version=PLANNER_VERSION,
    )


def _memory_plan(reason: str) -> ExecutionPlan:
    return ExecutionPlan(
        task=TaskType.CONVERSATION_MEMORY,
        reasoning=reason,
        confidence=1.0,
        steps=[ExecutionStep(tool=ToolName.CONVERSATION_MEMORY, description="Recall conversation history.")],
        requires_documents=False,
        requires_retrieval=False,
        requires_history=True,
        requires_general_knowledge=False,
        response_mode=ResponseMode.STREAM,
        planner_version=PLANNER_VERSION,
    )


def _detect_answer_length(query: str) -> str:
    """Infer Short / Medium / Detailed from the user query. Default Medium."""
    q = query.lower()
    if re.search(r"\b(briefly|in short|tl;?dr|concise|short answer|one sentence)\b", q):
        return "short"
    if re.search(r"\b(detailed|in[- ]depth|thorough(ly)?|comprehensive|elaborate|full explanation)\b", q):
        return "detailed"
    return "medium"


def _detect_intent(
    query: str,
    has_documents: bool,
    num_documents: int,
    has_history: bool = False,
) -> Optional[ExecutionPlan]:
    """
    Intent-based heuristic routing (not naive word prefixes).

    Classifies by communicative intent:
      - Document Transformation → DocumentReader
      - Fact Lookup → DocumentSearch
      - Comparison → DocumentReader (multi-doc)
      - Conversation Memory / Follow-up → ConversationMemory
      - Clear general knowledge → GeneralLLM (even if docs attached)
    """
    q = query.strip().lower()
    if not q:
        return None

    # Conversation memory / follow-ups (history-dependent)
    if has_history and (_has_any(_MEMORY_PATTERNS, q) or _has_any(_FOLLOWUP_PATTERNS, q)):
        return _memory_plan("Heuristic: conversation memory / follow-up intent.")

    if _has_any(_MEMORY_PATTERNS, q):
        return _memory_plan("Heuristic: conversation memory intent.")

    # Clear general-knowledge questions should not hijack document tools
    if _has_any(_GENERAL_KNOWLEDGE_PATTERNS, q):
        plan = _build_general_plan("Heuristic: general world-knowledge intent.")
        return plan

    if not has_documents:
        return None

    # Comparison across documents
    if _has_any(_COMPARE_PATTERNS, q) and num_documents >= 1:
        task = TaskType.DOCUMENT_COMPARISON if num_documents > 1 else TaskType.DOCUMENT_SUMMARY
        return _reader_plan(task, "Heuristic: document comparison intent.", num_documents)

    # Document transformation (summarize / rewrite / improve / translate / explain-this-doc)
    if _has_any(_TRANSFORM_PATTERNS, q):
        if num_documents > 1 and _has_any(_COMPARE_PATTERNS, q):
            return _reader_plan(TaskType.DOCUMENT_COMPARISON, "Heuristic: multi-doc transformation.", num_documents)
        if _has_any(_REWRITE_PATTERNS, q):
            return _reader_plan(TaskType.DOCUMENT_REWRITE, "Heuristic: document rewrite/improve intent.", num_documents)
        return _reader_plan(TaskType.DOCUMENT_SUMMARY, "Heuristic: document transformation intent.", num_documents)

    # Fact lookup / QA
    if _has_any(_FACT_LOOKUP_PATTERNS, q):
        # Guard: "explain this document" already handled by transform
        if re.search(r"explain (this|the|my) (document|file|pdf|synopsis)", q):
            return _reader_plan(TaskType.DOCUMENT_SUMMARY, "Heuristic: explain-document intent.", num_documents)
        return _search_plan("Heuristic: fact lookup intent.", query.strip())

    return None


def _build_general_plan(reason: str = "General knowledge request") -> ExecutionPlan:
    """Return a minimal, safe GENERAL plan backed by the GeneralLLM tool."""
    return ExecutionPlan(
        task=TaskType.GENERAL,
        reasoning=reason,
        confidence=1.0,
        steps=[
            ExecutionStep(
                tool=ToolName.GENERAL_LLM,
                description="Answer using general LLM knowledge.",
            )
        ],
        requires_general_knowledge=True,
        response_mode=ResponseMode.STREAM,
        planner_version=PLANNER_VERSION,
    )


def _build_fallback_plan(query: str, reason: str) -> ExecutionPlan:
    """Return a fallback plan with is_fallback=True for observability."""
    plan = _build_general_plan(reason)
    plan.is_fallback = True
    plan.fallback_reason = reason
    return plan


def _clean_llm_json(raw: str) -> str:
    """Strip markdown code fences and leading/trailing whitespace."""
    text = raw.strip()
    for fence in ("```json", "```JSON", "```"):
        if text.startswith(fence):
            text = text[len(fence):]
            break
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _parse_and_validate(raw: str, context: str) -> Optional[ExecutionPlan]:
    """Parse the LLM output and validate it as an ExecutionPlan."""
    try:
        clean = _clean_llm_json(raw)
        data = json.loads(clean)
        plan = ExecutionPlan(**data, planner_version=PLANNER_VERSION)
        return plan
    except Exception as exc:
        logger.warning(f"{context} Failed to parse/validate planner output: {exc}\nRaw output: {raw[:500]}")
        return None


class PlannerService:
    """
    LLM-powered Planner that produces ExecutionPlans.

    This is a service-level singleton — instantiate once per ConversationService.
    """

    def __init__(self) -> None:
        self._llm = DynamicLLMProvider()

    async def plan(
        self,
        request: PlannerRequest,
        *,
        pipeline_id: str = "",
        conversation_id: str = "",
    ) -> ExecutionPlan:
        """
        Generate an ExecutionPlan for the given PlannerRequest.

        This method NEVER raises. On any failure it returns a safe fallback plan.
        """
        ctx = f"[pipe={pipeline_id}] [conv={conversation_id}] [Planner]"
        start = time.time()
        answer_length = _detect_answer_length(request.query)

        # ------------------------------------------------------------------
        # 1. Heuristic fast-path: trivial greetings → skip LLM call entirely
        # ------------------------------------------------------------------
        if _is_greeting(request.query):
            plan = _build_general_plan("Heuristic: trivial greeting detected.")
            plan.answer_length = answer_length
            latency = int((time.time() - start) * 1000)
            logger.info(f"{ctx} Heuristic fast-path → GENERAL in {latency}ms")
            return plan

        # ------------------------------------------------------------------
        # 1b. Intent-based fast-path
        # ------------------------------------------------------------------
        num_docs = len(request.attached_document_titles) if request.attached_document_titles else 0
        has_history = bool(request.conversation_history)
        intent_plan = _detect_intent(
            request.query,
            request.has_documents,
            num_docs,
            has_history=has_history,
        )
        if intent_plan:
            intent_plan.answer_length = answer_length
            if intent_plan.task == TaskType.DOCUMENT_QA and not intent_plan.rewritten_query:
                intent_plan.rewritten_query = request.query
            latency = int((time.time() - start) * 1000)
            logger.info(f"{ctx} Heuristic intent fast-path → {intent_plan.task.value} in {latency}ms")
            return intent_plan

        # ------------------------------------------------------------------
        # 2. Trim request to stay within provider token limits
        # ------------------------------------------------------------------
        from tiktoken import get_encoding

        def _trim_request(req, max_input_tokens=5000):
            enc = get_encoding("cl100k_base")

            def _tokens(s: str) -> int:
                return len(enc.encode(s))

            titles = list(req.attached_document_titles)
            while titles and sum(_tokens(t) for t in titles) > max_input_tokens // 4:
                titles.pop(0)
            req.attached_document_titles = titles

            history = list(req.conversation_history)
            history = history[-ai_config.MAX_HISTORY_MESSAGES:]
            max_msg_tokens = (max_input_tokens // 2) // len(history) if history else 0
            for h in history:
                content = h.get("content", "")
                if _tokens(content) > max_msg_tokens:
                    words = content.split()
                    kept = []
                    cur = 0
                    for w in words:
                        if cur + _tokens(w + " ") > max_msg_tokens:
                            break
                        kept.append(w)
                        cur += _tokens(w + " ")
                    h["content"] = " ".join(kept) + " ..."
            req.conversation_history = history
            return req

        request = _trim_request(request)

        if request.has_documents and not request.attached_document_titles:
            request.attached_document_titles = ["(document)"]
        if not request.query.strip():
            request.query = "(no query)"

        # ------------------------------------------------------------------
        # 3. No documents → always GeneralLLM
        # ------------------------------------------------------------------
        if not request.has_documents:
            plan = _build_general_plan("No documents attached; using general knowledge.")
            plan.answer_length = answer_length
            latency = int((time.time() - start) * 1000)
            logger.info(f"{ctx} No-document fast-path → GENERAL in {latency}ms")
            return plan

        response_mode_override = request.response_mode_override

        prompt = build_planner_prompt(
            query=request.query,
            has_documents=request.has_documents,
            document_titles=request.attached_document_titles,
            documents_metadata=request.attached_documents_metadata,
            conversation_history=request.conversation_history,
            execution_context_summary=request.execution_context_summary,
        )

        raw_output = ""
        plan: Optional[ExecutionPlan] = None
        try:
            logger.info(f"{ctx} Calling LLM for plan generation…")
            raw_output = await self._llm.generate(prompt)
            plan = _parse_and_validate(raw_output, ctx)
        except Exception as exc:
            logger.warning(f"{ctx} LLM call failed on attempt 1: {exc}")

        if plan is None:
            logger.warning(f"{ctx} Plan invalid on attempt 1. Retrying with hint…")
            retry_prompt = (
                prompt
                + "\n\nIMPORTANT: Your previous response was not valid JSON. "
                "Output ONLY raw JSON. No markdown. No explanations. No code fences."
            )
            try:
                raw_output = await self._llm.generate(retry_prompt)
                plan = _parse_and_validate(raw_output, ctx)
            except Exception as exc:
                logger.error(f"{ctx} LLM call failed on attempt 2: {exc}")

        if plan is None:
            logger.error(
                f"{ctx} Both planner attempts failed. Using GENERAL fallback. "
                f"Last raw output: {raw_output[:300]}"
            )
            plan = _build_fallback_plan(
                request.query,
                reason="Planner LLM output was invalid after 2 attempts.",
            )

        if response_mode_override:
            if response_mode_override == "GENERAL_ONLY":
                plan.steps = [
                    ExecutionStep(
                        tool=ToolName.GENERAL_LLM,
                        description="Forced GENERAL_ONLY mode by API request.",
                    )
                ]
                plan.requires_documents = False
                plan.requires_retrieval = False
            elif response_mode_override == "KNOWLEDGE_ONLY":
                plan.steps = [s for s in plan.steps if s.tool in (
                    ToolName.DOCUMENT_READER, ToolName.DOCUMENT_SEARCH
                )]
                if not plan.steps:
                    plan.steps = [
                        ExecutionStep(
                            tool=ToolName.DOCUMENT_SEARCH,
                            description="Forced KNOWLEDGE_ONLY mode by API request.",
                        )
                    ]
                plan.requires_general_knowledge = False

        if not request.has_documents:
            doc_tools = {ToolName.DOCUMENT_READER, ToolName.DOCUMENT_SEARCH}
            if any(s.tool in doc_tools for s in plan.steps):
                logger.warning(
                    f"{ctx} Plan requested document tools but no documents attached. "
                    "Downgrading to GENERAL."
                )
                plan = _build_fallback_plan(
                    request.query,
                    reason="Plan requested documents but none are attached.",
                )

        plan.answer_length = answer_length
        plan.max_chunks = min(plan.max_chunks or ai_config.MAX_CHUNKS, ai_config.MAX_CHUNKS)

        latency = int((time.time() - start) * 1000)
        logger.info(
            f"{ctx} Plan generated: task={plan.task.value} "
            f"steps={[s.tool.value for s in plan.steps]} "
            f"fallback={plan.is_fallback} "
            f"answer_length={plan.answer_length} "
            f"latency={latency}ms"
        )
        return plan
