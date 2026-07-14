"""
Executor Schemas — Milestone 10

Defines the types used exclusively within the Executor layer:
  - ExecutionContext: everything a tool needs, injected at execution time.
  - StepResult: the output of a single tool step.
  - ExecutorMetrics: timing/cost data collected during execution.
  - FinalResponse: the Executor's output returned to the ConversationService.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Execution Context
# ---------------------------------------------------------------------------

@dataclass
class ExecutionContext:
    """
    Everything a tool can ever need, passed as a single object.

    Design contract:
        - NEVER pass raw kwargs between tools.
        - NEVER store per-request state outside this context.
        - Tools MUST NOT add new attributes to this object.
        - Executor creates exactly one context per request.
    """

    # Identity
    pipeline_id: str
    request_id: str
    conversation_id: str
    user_id: str

    # Database access
    db: AsyncSession

    # Document information (populated from DB before Executor.run)
    attached_document_ids: List[str] = field(default_factory=list)
    attached_document_titles: List[str] = field(default_factory=list)
    attached_documents: List[Dict[str, Any]] = field(default_factory=list)

    # Conversation history (populated by ConversationMemoryTool or pre-loaded)
    history: List[Dict[str, str]] = field(default_factory=list)

    # Accumulated tool outputs (filled in as steps complete)
    # Keys are step_ids; values are the tool's output dict.
    step_outputs: Dict[str, Any] = field(default_factory=dict)

    # Raw user query (never rewritten — the rewritten query lives in the plan)
    raw_query: str = ""

    # System Configuration (from ai_config)
    config: Dict[str, Any] = field(default_factory=dict)

    # Current execution state (for status tracking and observability)
    current_execution_state: Dict[str, Any] = field(default_factory=dict)

    # Logger tag (for structured logging inside tools)
    log_prefix: str = ""

    def __post_init__(self):
        self.log_prefix = (
            f"[pipe={self.pipeline_id}] [req={self.request_id}] "
            f"[conv={self.conversation_id}] [user={self.user_id}]"
        )


# ---------------------------------------------------------------------------
# Step Result
# ---------------------------------------------------------------------------

@dataclass
class StepResult:
    """The output of a single ExecutionStep."""

    step_id: str
    tool_name: str
    success: bool
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    latency_ms: int = 0
    retried: bool = False


# ---------------------------------------------------------------------------
# Executor Metrics
# ---------------------------------------------------------------------------

@dataclass
class ExecutorMetrics:
    """Timing and cost data collected across all steps."""

    planner_latency_ms: int = 0
    total_tool_latency_ms: int = 0
    llm_latency_ms: int = 0
    total_latency_ms: int = 0

    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0

    retries: int = 0
    steps_executed: int = 0
    steps_failed: int = 0


# ---------------------------------------------------------------------------
# Final Response
# ---------------------------------------------------------------------------

@dataclass
class FinalResponse:
    """
    The Executor's complete output, handed back to the ConversationService.

    The ConversationService uses this to:
        1. Return the answer to the API layer.
        2. Persist messages to the database.
        3. Populate the debug panel.
    """

    answer: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    retrieved_chunks: List[Dict[str, Any]] = field(default_factory=list)
    provenance: str = "general"

    # Observability data
    plan_dump: Dict[str, Any] = field(default_factory=dict)
    step_results: List[StepResult] = field(default_factory=list)
    metrics: ExecutorMetrics = field(default_factory=ExecutorMetrics)

    # Error state (populated when execution partially or fully fails)
    error: Optional[str] = None
    partial: bool = False  # True if some steps failed but we still have an answer
