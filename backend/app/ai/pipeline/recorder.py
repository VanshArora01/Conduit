"""
Pipeline Recorder — Milestone 10 (extended)

Stores rich execution data for the Developer Panel.
Extended to include:
  - planner_plan: full ExecutionPlan dump
  - tool_graph: per-step decision log
  - step_results: each StepResult's success/latency/output
  - executor_metrics: timing, token counts, cost
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class PipelineExecution(BaseModel):
    pipeline_id: str
    request_id: str
    conversation_id: str
    user_id: str

    # Request details
    request: Dict[str, Any] = Field(default_factory=dict)

    # Planner details — now includes the full ExecutionPlan dump
    planner: Dict[str, Any] = Field(default_factory=dict)

    # NEW: Full ExecutionPlan (Milestone 10)
    planner_plan: Dict[str, Any] = Field(default_factory=dict)

    # Retrieval details (raw_chunks, scores, document_ids, chunk_ids, etc.)
    retrieval: Dict[str, Any] = Field(default_factory=dict)

    # Context optimizer details
    optimizer: Dict[str, Any] = Field(default_factory=dict)

    # Prompt building details
    prompt: Dict[str, Any] = Field(default_factory=dict)

    # Generation details (completion, finish_reason, latency_ms, tokens)
    generation: Dict[str, Any] = Field(default_factory=dict)

    # Streaming details
    stream: Dict[str, Any] = Field(default_factory=dict)

    # NEW: Per-step execution results (Milestone 10)
    tool_graph: List[Dict[str, Any]] = Field(default_factory=list)

    # NEW: Aggregated executor metrics (Milestone 10)
    executor_metrics: Dict[str, Any] = Field(default_factory=dict)

    # Timing durations per stage (ms)
    timings: Dict[str, Any] = Field(default_factory=dict)

    # Error logs and tracebacks
    errors: List[str] = Field(default_factory=list)

    # Final state status
    completed: bool = False


# Global in-memory registry for recent pipeline executions
pipeline_registry: Dict[str, PipelineExecution] = {}


def get_pipeline_execution(pipeline_id: str) -> Optional[PipelineExecution]:
    return pipeline_registry.get(pipeline_id)


def register_pipeline_execution(execution: PipelineExecution):
    pipeline_registry[execution.pipeline_id] = execution
    # Keep only the last 100 executions to prevent memory leaks
    if len(pipeline_registry) > 100:
        first_key = next(iter(pipeline_registry))
        pipeline_registry.pop(first_key, None)
