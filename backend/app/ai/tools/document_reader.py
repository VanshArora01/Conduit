"""
DocumentReaderTool — Milestone 10

Reads the FULL text of one or more attached documents.

Use case: Summarisation, rewriting, translation, comparison.
NOT for: targeted Q&A (use DocumentSearchTool instead).

Strategy:
  1. Load document rows from the database (storage_path or processed_content).
  2. If processed_content is available (set during indexing), use it directly.
  3. If only storage_path is available, read the file from disk.
  4. If the combined text fits within the context window limit, return it all.
  5. If too large, split into sequential chunks and return the first N chunks
     whose combined token count stays within max_context_tokens.
  6. Return a dict with {"chunks": [...], "document_titles": [...], "full_text": "..."}.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from sqlalchemy import select

from app.ai.config import ai_config
from app.ai.tools.base import BaseTool, RetryPolicy, ToolMeta
from app.models.conversation import ConversationDocument
from app.models.document import Document

logger = logging.getLogger(__name__)

# Approximate max chars to return before chunking (1 token ≈ 4 chars)
_MAX_CHARS = ai_config.MAX_CONTEXT_TOKENS * 4


class DocumentReaderTool(BaseTool):
    """
    Load and return the full text of one or more attached documents.

    This tool never performs semantic search. It reads documents sequentially
    and returns their complete content (or as much as fits in context).
    """

    meta = ToolMeta(
        name="document_reader",
        description="Load and read the full text of attached documents.",
        capabilities=["document_reading", "full_text_loading", "multi_document"],
        supports_streaming=False,
        requires_auth=False,
        timeout_seconds=20,
        retry_policy=RetryPolicy(max_attempts=2, backoff_seconds=0.5),
        estimated_cost_per_call_usd=0.0,
    )

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Any,
    ) -> Dict[str, Any]:
        """
        Load document content for the documents attached to this conversation.

        Returns:
            {
                "chunks": [{"document_title": str, "content": str, "chunk_index": int}],
                "document_titles": [str],
                "full_text": str,    # concatenated content of all documents
                "source": "document_reader"
            }
        """
        db = context.db
        doc_ids = context.attached_document_ids
        conv_id = context.conversation_id
        log_pfx = context.log_prefix

        if not doc_ids:
            logger.warning(f"{log_pfx} [DocumentReader] No document IDs in context.")
            return {"chunks": [], "document_titles": [], "full_text": "", "source": "document_reader"}

        # Fetch document rows
        result = await db.execute(
            select(Document).where(Document.id.in_(doc_ids))
        )
        documents: List[Document] = result.scalars().all()

        if not documents:
            logger.warning(f"{log_pfx} [DocumentReader] No documents found in DB for IDs: {doc_ids}")
            return {"chunks": [], "document_titles": [], "full_text": "", "source": "document_reader"}

        chunks = []
        document_titles = []
        full_parts = []

        for doc in documents:
            title = doc.title
            document_titles.append(title)

            # --- Try to use processed_content (set during indexing) ---
            content = ""
            if doc.processed_content:
                content = doc.processed_content.strip()
                logger.info(f"{log_pfx} [DocumentReader] Using processed_content for '{title}' ({len(content)} chars)")
            elif doc.storage_path:
                # Fall back to reading from disk
                try:
                    content = _read_from_disk(doc.storage_path, title, log_pfx)
                except Exception as exc:
                    logger.error(f"{log_pfx} [DocumentReader] Failed to read '{title}' from disk: {exc}")
                    content = f"[ERROR: Could not read document '{title}']"
            else:
                logger.warning(f"{log_pfx} [DocumentReader] Document '{title}' has no content or storage_path.")
                content = f"[No content available for '{title}']"

            full_parts.append(f"=== Document: {title} ===\n{content}")

            # Split into chunks if needed
            doc_chunks = _split_to_chunks(content, title)
            chunks.extend(doc_chunks)

        full_text = "\n\n".join(full_parts)

        # Truncate full_text to context window limit
        if len(full_text) > _MAX_CHARS:
            full_text = full_text[:_MAX_CHARS] + "\n\n[...content truncated to fit context window...]"
            logger.info(f"{log_pfx} [DocumentReader] Full text truncated to {_MAX_CHARS} chars.")

        logger.info(
            f"{log_pfx} [DocumentReader] Loaded {len(documents)} document(s), "
            f"{len(chunks)} chunk(s), {len(full_text)} chars total."
        )

        return {
            "chunks": chunks,
            "document_titles": document_titles,
            "full_text": full_text,
            "source": "document_reader",
        }


def _read_from_disk(storage_path: str, title: str, log_pfx: str) -> str:
    """Read text content from the storage path on disk."""
    if not os.path.exists(storage_path):
        raise FileNotFoundError(f"Storage path does not exist: {storage_path}")

    # Text-based formats
    text_extensions = {".txt", ".md", ".csv", ".json", ".xml", ".html", ".rst"}
    _, ext = os.path.splitext(storage_path.lower())

    if ext in text_extensions:
        with open(storage_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        logger.info(f"{log_pfx} [DocumentReader] Read {len(content)} chars from disk: {storage_path}")
        return content

    # For binary formats (PDF, DOCX) we rely on processed_content being set during indexing.
    # If we reach here, it means indexing didn't store processed_content — flag this.
    logger.warning(
        f"{log_pfx} [DocumentReader] Binary file '{title}' at '{storage_path}' "
        "has no processed_content. Indexing may be incomplete."
    )
    return f"[Binary document '{title}' could not be read directly. Ensure indexing completed.]"


def _split_to_chunks(content: str, title: str) -> List[Dict[str, Any]]:
    """
    Split content into sequential chunks for structured output.

    Each chunk is a dict compatible with the retrieval chunk format used
    by the PromptBuilder.
    """
    chunk_size = ai_config.DEFAULT_CHUNK_SIZE  # chars
    chunks = []

    if len(content) <= chunk_size:
        chunks.append({
            "score": 1.0,
            "payload": {
                "document_title": title,
                "provider": "document_reader",
                "chunk_index": 0,
                "content": content,
            }
        })
        return chunks

    # Split on paragraph boundaries first, then hard-cut if needed
    paragraphs = content.split("\n\n")
    current = []
    current_len = 0
    chunk_index = 0

    for para in paragraphs:
        para_len = len(para)
        if current_len + para_len > chunk_size and current:
            chunks.append({
                "score": 1.0,
                "payload": {
                    "document_title": title,
                    "provider": "document_reader",
                    "chunk_index": chunk_index,
                    "content": "\n\n".join(current),
                }
            })
            chunk_index += 1
            current = [para]
            current_len = para_len
        else:
            current.append(para)
            current_len += para_len

    if current:
        chunks.append({
            "score": 1.0,
            "payload": {
                "document_title": title,
                "provider": "document_reader",
                "chunk_index": chunk_index,
                "content": "\n\n".join(current),
            }
        })

    return chunks
