"""
GeneralLLMTool — Milestone 10

A thin, stateless wrapper around DynamicLLMProvider.

Use case:
  - Answering general knowledge questions (no documents).
  - Generating final answers in HYBRID tasks.
  - Responding to greetings and conversational messages.

This tool is intentionally simple. It does NOT perform retrieval.
It does NOT load documents. It receives a prompt (from the Executor's
PromptBuilder) and returns the LLM's response.

Returns:
  {
    "response": str,
    "prompt_tokens": int,
    "completion_tokens": int,
    "latency_ms": int,
    "cost": float,
    "finish_reason": str,
    "source": "general_llm"
  }
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Dict

from app.ai.config import ai_config
from app.ai.llm.manager import DynamicLLMProvider
from app.ai.tools.base import BaseTool, RetryPolicy, ToolMeta

logger = logging.getLogger(__name__)


class GeneralLLMTool(BaseTool):
    """
    Invoke the configured LLM provider with a prompt.

    The Executor builds the final prompt (combining tool outputs, context,
    history) and then calls this tool to get the final user-facing answer.
    This tool is also used for pure general-knowledge queries with no documents.
    """

    meta = ToolMeta(
        name="general_llm",
        description="Invoke the LLM with general knowledge (no document retrieval).",
        capabilities=["text_generation", "general_knowledge", "conversational"],
        supports_streaming=True,
        requires_auth=False,
        timeout_seconds=ai_config.TIMEOUT_LLM,
        retry_policy=RetryPolicy(max_attempts=2, backoff_seconds=1.0),
        estimated_cost_per_call_usd=0.0001,  # approximate; updated post-call
    )

    def __init__(self) -> None:
        self._llm = DynamicLLMProvider()

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Any,
    ) -> Dict[str, Any]:
        """
        Generate a response from the LLM.

        input_data keys consumed:
          - prompt (str): the full prompt to send. Required.
          - stream (bool): if True, the Executor handles streaming separately.
        """
        log_pfx = context.log_prefix
        prompt = input_data.get("prompt", "")
        if not prompt:
            logger.error(f"{log_pfx} [GeneralLLM] No prompt provided.")
            return {
                "response": "",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "latency_ms": 0,
                "cost": 0.0,
                "finish_reason": "error",
                "source": "general_llm",
                "error": "No prompt provided.",
            }

        logger.info(f"{log_pfx} [GeneralLLM] Generating response (prompt_len={len(prompt)})…")

        response = await self._llm.generate(prompt)
        metrics = getattr(self._llm, "last_metrics", {})

        logger.info(
            f"{log_pfx} [GeneralLLM] Response generated: "
            f"tokens={metrics.get('completion_tokens', 0)} "
            f"latency={metrics.get('latency_ms', 0)}ms "
            f"cost=${metrics.get('cost', 0.0):.6f}"
        )

        return {
            "response": response,
            "prompt_tokens": metrics.get("prompt_tokens", 0),
            "completion_tokens": metrics.get("completion_tokens", 0),
            "latency_ms": metrics.get("latency_ms", 0),
            "cost": metrics.get("cost", 0.0),
            "finish_reason": metrics.get("finish_reason", "stop"),
            "source": "general_llm",
        }

    async def stream(
        self,
        prompt: str,
        context: Any,
    ) -> AsyncGenerator[str, None]:
        """
        Stream tokens from the LLM. Called directly by the Executor for streaming.

        This is a separate method (not execute) because streaming changes the
        response shape — it yields chunks instead of returning a dict.
        """
        log_pfx = context.log_prefix
        logger.info(f"{log_pfx} [GeneralLLM] Streaming response…")
        async for chunk in self._llm.generate_stream(prompt):
            yield chunk
