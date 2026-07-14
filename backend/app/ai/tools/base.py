"""
BaseTool — Abstract base class for all Conduit tools.

Every tool must subclass BaseTool and implement:
  - class-level metadata attributes (name, description, capabilities, etc.)
  - async execute(input_data, context) -> dict

The Executor calls tools ONLY via this interface. It never instantiates
tools directly — it uses the ToolRegistry.

Future tool authors:
  1. Subclass BaseTool in a new file under app/ai/tools/.
  2. Implement the execute() method.
  3. Register in app/ai/tools/registry.py.
  That's it. Zero Executor changes required.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RetryPolicy:
    """Retry configuration for a tool."""
    max_attempts: int = 2          # Total attempts (1 = no retry)
    backoff_seconds: float = 0.5   # Delay between retries


@dataclass
class ToolMeta:
    """
    Rich metadata about a tool.

    This is used by:
      - The Executor (retry_policy, timeout_seconds)
      - The Developer Panel (capabilities, cost, description)
      - Future orchestrators (supports_streaming, requires_auth)
    """
    name: str
    description: str
    capabilities: List[str] = field(default_factory=list)
    supports_streaming: bool = False
    requires_auth: bool = False
    timeout_seconds: int = 30
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    estimated_cost_per_call_usd: float = 0.0
    input_schema: Optional[str] = None    # JSON Schema description (future)
    output_schema: Optional[str] = None   # JSON Schema description (future)


class BaseTool(ABC):
    """
    Abstract base class that all Conduit tools must implement.

    Tools are stateless — all request-specific data flows through
    ExecutionContext, not through instance variables.
    """

    # Class-level metadata — override in each subclass.
    meta: ToolMeta = ToolMeta(name="base", description="Abstract base tool")

    @abstractmethod
    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Any,          # ExecutionContext — typed as Any to avoid circular import
    ) -> Dict[str, Any]:
        """
        Execute the tool and return a result dict.

        Args:
            input_data: Tool-specific configuration from ExecutionStep.config
                        merged with plan-level fields (query, max_chunks, etc.).
            context:    ExecutionContext — the single source of truth for all
                        request-scoped data (db session, documents, history, etc.)

        Returns:
            A dict whose keys the Executor will merge into context.step_outputs.
            The exact keys are tool-specific; document tools typically return
            {"chunks": [...]} while LLM tools return {"response": "..."}.

        Raises:
            Should not raise unless the failure is unrecoverable.
            Transient errors should be propagated so the Executor can retry.
        """
        ...
