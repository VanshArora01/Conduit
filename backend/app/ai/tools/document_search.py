"""
DocumentSearchTool — Milestone 10

Semantically searches attached documents using embeddings + Qdrant.

Use case: Targeted Q&A, fact extraction, specific concept lookup.
NOT for: tasks that need the full document text (use DocumentReaderTool).

Flow:
  1. Determine the search query (use rewritten_query from plan if available).
  2. Embed the query using the configured embedding provider.
  3. Build Qdrant filters scoped to the conversation's attached documents.
  4. Query Qdrant for top-K chunks.
  5. Apply similarity threshold filter.
  6. Run through ContextOptimizer (rerank + compress adjacent chunks).
  7. Return structured chunk list.

Returns:
  {
    "chunks": [{"score": float, "payload": {...}}],
    "raw_chunks": [...],             # pre-optimization, for observability
    "filtered_chunks": [...],        # after threshold, before compression
    "optimized_chunks": [...],       # final selected chunks
    "retrieval_records": [...],      # per-chunk decision log for Developer Panel
    "query_used": str,
    "source": "document_search"
  }
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.ai.config import ai_config
from app.ai.embeddings.huggingface import HuggingFaceEmbeddingProvider
from app.ai.retrieval.optimizer import ContextOptimizer
from app.ai.tools.base import BaseTool, RetryPolicy, ToolMeta
from app.ai.vectorstore.qdrant import QdrantVectorStore

logger = logging.getLogger(__name__)

_THRESHOLD_HIGH = ai_config.SIMILARITY_THRESHOLD_HIGH
_THRESHOLD_MEDIUM = ai_config.SIMILARITY_THRESHOLD_MEDIUM
_THRESHOLD_LOW = ai_config.SIMILARITY_THRESHOLD_LOW


class DocumentSearchTool(BaseTool):
    """
    Semantic search over Qdrant for attached documents.

    This tool performs embedding-based retrieval and returns ranked,
    compressed, relevant chunks. It does NOT read full documents.
    """

    meta = ToolMeta(
        name="document_search",
        description="Semantically search attached documents for relevant chunks.",
        capabilities=["semantic_search", "vector_retrieval", "chunk_ranking"],
        supports_streaming=False,
        requires_auth=False,
        timeout_seconds=ai_config.TIMEOUT_RETRIEVAL,
        retry_policy=RetryPolicy(max_attempts=2, backoff_seconds=0.3),
        estimated_cost_per_call_usd=0.0,
    )

    def __init__(self) -> None:
        self._embedding_provider = HuggingFaceEmbeddingProvider()
        self._vector_store = QdrantVectorStore()
        self._optimizer = ContextOptimizer()

    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Any,
    ) -> Dict[str, Any]:
        """
        Execute semantic search over attached documents.

        input_data keys consumed:
          - query (str): overrides context.raw_query if provided
          - max_chunks (int): maximum final chunks to return
          - similarity_threshold (float): override default threshold

        context keys consumed:
          - raw_query
          - attached_document_ids
        """
        log_pfx = context.log_prefix
        doc_ids = context.attached_document_ids
        if not doc_ids:
            logger.warning(f"{log_pfx} [DocumentSearch] No document IDs in context.")
            return _empty_result()

        # Determine search query
        query = input_data.get("query") or context.raw_query
        max_chunks = int(input_data.get("max_chunks", ai_config.MAX_CHUNKS))
        task = input_data.get("task", "UNKNOWN")

        if not query:
            logger.warning(f"{log_pfx} [DocumentSearch] Empty query — returning empty result.")
            return _empty_result()

        logger.info(f"{log_pfx} [DocumentSearch] Query='{query}' docs={doc_ids} max_chunks={max_chunks}")

        # 1. Embed query
        query_vector = self._embedding_provider.embed_text(query)
        if not query_vector:
            logger.error(f"{log_pfx} [DocumentSearch] Embedding returned empty vector.")
            return _empty_result()

        # 2. Build Qdrant filter scoped to attached documents
        filters = {"document_id": doc_ids}

        # 3. Search Qdrant
        raw_chunks = await self._vector_store.similarity_search(
            collection_name=self._vector_store.collection_name,
            query_vector=query_vector,
            limit=ai_config.RETRIEVAL_TOP_K,
            filter_criteria=filters,
        )

        logger.info(f"{log_pfx} [DocumentSearch] Retrieved {len(raw_chunks)} raw chunks from Qdrant.")

        # Tag raw chunks with their similarity band
        for c in raw_chunks:
            s = c.get("score", 0.0)
            if s >= _THRESHOLD_HIGH:
                c["band"] = "High"
            elif s >= _THRESHOLD_MEDIUM:
                c["band"] = "Medium"
            elif s >= _THRESHOLD_LOW:
                c["band"] = "Low"
            else:
                c["band"] = "Noise"

        # 4. Apply threshold based on task type
        # For normal QA, ignore Low chunks (require Medium). For summaries/comparison, allow Low.
        # Noise (< 0.35) is always dropped.
        if task in ["DOCUMENT_SUMMARY", "DOCUMENT_COMPARISON"]:
            min_threshold = _THRESHOLD_LOW
        else:
            min_threshold = _THRESHOLD_MEDIUM
            
        filtered_chunks = [c for c in raw_chunks if c.get("score", 0.0) >= min_threshold]

        # 5. Optimize (rerank + compress adjacent chunks)
        optimized_chunks = self._optimizer.optimize(filtered_chunks, max_chunks=max_chunks)

        # Preserve band tags on optimized chunks for Developer Panel
        for oc in optimized_chunks:
            if "band" not in oc:
                s = oc.get("score", 0.0)
                if s >= _THRESHOLD_HIGH:
                    oc["band"] = "High"
                elif s >= _THRESHOLD_MEDIUM:
                    oc["band"] = "Medium"
                elif s >= _THRESHOLD_LOW:
                    oc["band"] = "Low"
                else:
                    oc["band"] = "Noise"

        # 6. Build per-chunk decision log (for Developer Panel — includes Low/Noise)
        retrieval_records = _build_records(raw_chunks, optimized_chunks, min_threshold)

        logger.info(
            f"{log_pfx} [DocumentSearch] "
            f"raw={len(raw_chunks)} filtered={len(filtered_chunks)} "
            f"optimized={len(optimized_chunks)}"
        )

        return {
            "chunks": optimized_chunks,
            "raw_chunks": raw_chunks,
            "filtered_chunks": filtered_chunks,
            "optimized_chunks": optimized_chunks,
            "retrieval_records": retrieval_records,
            "query_used": query,
            "source": "document_search",
        }


def _empty_result() -> Dict[str, Any]:
    return {
        "chunks": [],
        "raw_chunks": [],
        "filtered_chunks": [],
        "optimized_chunks": [],
        "retrieval_records": [],
        "query_used": "",
        "source": "document_search",
    }


def _build_records(
    raw_chunks: List[Dict],
    optimized_chunks: List[Dict],
    threshold: float,
) -> List[Dict[str, Any]]:
    """Build a per-chunk decision log for the Developer Panel."""
    records = []
    optimized_ids = {id(c) for c in optimized_chunks}
    for chunk in raw_chunks:
        score = chunk.get("score", 0.0)
        band = chunk.get("band", "Unknown")
        payload = chunk.get("payload", {})
        is_selected = id(chunk) in optimized_ids

        if is_selected:
            reason = f"Selected (score={score:.3f}, band={band})"
        elif score < threshold:
            reason = f"Dropped below task threshold ({score:.3f} < {threshold}, band={band})"
        else:
            reason = f"Dropped by Optimizer (token/chunk limit, band={band})"

        records.append({
            "chunk_id": chunk.get("id", "N/A"),
            "score": score,
            "band": band,
            "document_title": payload.get("document_title", "Unknown"),
            "selected": is_selected,
            "reason": reason,
        })
    return records
