"""
ConversationMemoryTool — Milestone 10

Fetches recent conversation history from the database.

The Planner may include this step when:
  - The user's query references a previous turn ("as you mentioned earlier…").
  - The task type is CONVERSATION_MEMORY.

This tool queries the ConversationMessage table and returns the last
N messages formatted for inclusion in the LLM prompt.

Returns:
  {
    "history": [{"role": str, "content": str}],
    "message_count": int,
    "source": "conversation_memory"
  }
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from sqlalchemy import select

from app.ai.config import ai_config
from app.ai.tools.base import BaseTool, RetryPolicy, ToolMeta
from app.models.conversation import ConversationMessage

logger = logging.getLogger(__name__)


class ConversationMemoryTool(BaseTool):
    """
    Retrieve recent conversation history from the database.

    This tool is stateless — it reads from the database on each call.
    The Executor stores the history in context so subsequent tools can use it.
    """

    meta = ToolMeta(
        name="conversation_memory",
        description="Retrieve recent conversation history from the database.",
        capabilities=["memory_retrieval", "history_lookup", "context_enrichment"],
        supports_streaming=False,
        requires_auth=False,
        timeout_seconds=5,
        retry_policy=RetryPolicy(max_attempts=2, backoff_seconds=0.2),
        estimated_cost_per_call_usd=0.0,
    )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Any,
    ) -> Dict[str, Any]:
        """
        Fetch conversation history from the database.

        input_data keys consumed:
          - max_messages (int): number of messages to retrieve (default from config)

        context keys consumed:
          - db
          - conversation_id
        """
        log_pfx = context.log_prefix
        db = context.db
        conversation_id = context.conversation_id
        max_messages = int(input_data.get("max_messages", ai_config.MAX_HISTORY_MESSAGES))

        try:
            import uuid as _uuid
            conv_uuid = _uuid.UUID(conversation_id) if isinstance(conversation_id, str) else conversation_id

            result = await db.execute(
                select(ConversationMessage)
                .where(ConversationMessage.conversation_id == conv_uuid)
                .order_by(ConversationMessage.created_at.desc())
                .limit(max_messages)
            )
            messages: List[ConversationMessage] = result.scalars().all()
            # Reverse to get chronological order
            messages = list(reversed(messages))

            history = [{"role": m.role, "content": m.content} for m in messages]

            # Store in context for downstream tools
            context.history = history

            logger.info(
                f"{log_pfx} [ConversationMemory] Retrieved {len(history)} messages "
                f"from conversation {conversation_id}."
            )

            return {
                "history": history,
                "message_count": len(history),
                "source": "conversation_memory",
            }

        except Exception as exc:
            logger.error(f"{log_pfx} [ConversationMemory] Failed to retrieve history: {exc}", exc_info=True)
            return {
                "history": [],
                "message_count": 0,
                "source": "conversation_memory",
                "error": str(exc),
            }
