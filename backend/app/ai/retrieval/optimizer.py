from typing import List, Dict, Any
import logging

from app.ai.config import ai_config

logger = logging.getLogger(__name__)


class ContextOptimizer:
    """
    Optimizes retrieved chunks by re-ranking, deduplicating, and compressing them.
    """

    def optimize(self, chunks: List[Dict[str, Any]], max_chunks: int = 5) -> List[Dict[str, Any]]:
        if not chunks:
            return []

        # 1. Re-rank (Already sorted by score from Qdrant, but we can enforce it)
        sorted_chunks = sorted(chunks, key=lambda x: x.get("score", 0.0), reverse=True)

        # 2. Group by document and sort by chunk_index for compression
        doc_groups: Dict[str, List[Dict[str, Any]]] = {}
        for chunk in sorted_chunks:
            payload = chunk.get("payload", {})
            doc_title = payload.get("document_title", "Unknown")
            doc_key = f"{doc_title}_{payload.get('provider', '')}"

            if doc_key not in doc_groups:
                doc_groups[doc_key] = []
            doc_groups[doc_key].append(chunk)

        # 3. Compress adjacent or overlapping chunks
        compressed_chunks: List[Dict[str, Any]] = []

        for _doc_key, doc_chunks in doc_groups.items():
            doc_chunks.sort(key=lambda x: x.get("payload", {}).get("chunk_index", 0))

            merged_payloads = []
            current_merged = None

            for chunk in doc_chunks:
                payload = chunk.get("payload", {})
                score = chunk.get("score", 0.0)

                if current_merged is None:
                    current_merged = {
                        "document_title": payload.get("document_title"),
                        "provider": payload.get("provider"),
                        "start_index": payload.get("chunk_index", 0),
                        "end_index": payload.get("chunk_index", 0),
                        "content": payload.get("content", ""),
                        "max_score": score,
                    }
                else:
                    if payload.get("chunk_index", 0) <= current_merged["end_index"] + 1:
                        if payload.get("content", "") not in current_merged["content"]:
                            current_merged["content"] += "\n...\n" + payload.get("content", "")

                        current_merged["end_index"] = max(
                            current_merged["end_index"], payload.get("chunk_index", 0)
                        )
                        current_merged["max_score"] = max(current_merged["max_score"], score)
                    else:
                        merged_payloads.append(current_merged)
                        current_merged = {
                            "document_title": payload.get("document_title"),
                            "provider": payload.get("provider"),
                            "start_index": payload.get("chunk_index", 0),
                            "end_index": payload.get("chunk_index", 0),
                            "content": payload.get("content", ""),
                            "max_score": score,
                        }

            if current_merged:
                merged_payloads.append(current_merged)

            for mp in merged_payloads:
                s = mp["max_score"]
                if s >= ai_config.SIMILARITY_THRESHOLD_HIGH:
                    band = "High"
                elif s >= ai_config.SIMILARITY_THRESHOLD_MEDIUM:
                    band = "Medium"
                elif s >= ai_config.SIMILARITY_THRESHOLD_LOW:
                    band = "Low"
                else:
                    band = "Noise"
                compressed_chunks.append({
                    "score": mp["max_score"],
                    "band": band,
                    "payload": {
                        "document_title": mp["document_title"],
                        "provider": mp["provider"],
                        "chunk_index": (
                            f"{mp['start_index']}-{mp['end_index']}"
                            if mp["start_index"] != mp["end_index"]
                            else mp["start_index"]
                        ),
                        "content": mp["content"],
                    },
                })

        # 4. Final re-rank of compressed chunks by max_score and limit to max_chunks
        final_chunks = sorted(compressed_chunks, key=lambda x: x.get("score", 0.0), reverse=True)

        logger.info(
            f"Context Optimizer: Compressed {len(chunks)} raw chunks into "
            f"{len(final_chunks)} merged blocks. Keeping top {max_chunks}."
        )
        return final_chunks[:max_chunks]
