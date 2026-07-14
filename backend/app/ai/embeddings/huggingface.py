import logging
from typing import List
from fastapi import HTTPException
from fastembed import TextEmbedding
from app.ai.interfaces.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)

class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str | None = None):
        # We switch to fastembed to run embeddings locally, completely avoiding HuggingFace API token issues!
        # This defaults to BAAI/bge-base-en-v1.5 which is very fast, high quality, and produces 768-dim vectors matching our Qdrant DB.
        self.model_name = model_name or "BAAI/bge-base-en-v1.5"
        self.embedding_model = TextEmbedding(model_name=self.model_name)

    def embed_text(self, text: str) -> List[float]:
        try:
            logger.info(f"Generating local embedding for text with FastEmbed model {self.model_name}")
            embeddings = list(self.embedding_model.embed([text]))
            if embeddings and len(embeddings) > 0:
                # fastembed returns numpy arrays, we convert to float list
                return embeddings[0].tolist()
            return []
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Embedding error: {str(e)}")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        try:
            logger.info(f"Generating local embeddings for {len(texts)} texts with FastEmbed model {self.model_name}")
            embeddings = list(self.embedding_model.embed(texts))
            return [e.tolist() for e in embeddings]
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Embedding error: {str(e)}")
