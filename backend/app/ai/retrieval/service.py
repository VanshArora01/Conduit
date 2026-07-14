from typing import List, Dict, Any, Optional
import logging
from app.ai.interfaces.retrieval import RetrievalService as IRetrievalService
from app.ai.embeddings.huggingface import HuggingFaceEmbeddingProvider
from app.ai.vectorstore.qdrant import QdrantVectorStore

logger = logging.getLogger(__name__)

class RetrievalService(IRetrievalService):
    def __init__(self):
        self.embedding_provider = HuggingFaceEmbeddingProvider()
        self.vector_store = QdrantVectorStore()

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        logger.info(f"Retrieving top {top_k} chunks for query: '{query}' with filters: {filters}")
        
        # Embed the query
        query_vector = self.embedding_provider.embed_text(query)
        
        # Search Qdrant
        # We assume collection_name=None will use the default collection defined in QdrantVectorStore
        results = await self.vector_store.similarity_search(
            collection_name=self.vector_store.collection_name,
            query_vector=query_vector,
            limit=top_k,
            filter_criteria=filters
        )
        
        # Apply similarity threshold if provided
        if similarity_threshold is not None:
            results = [res for res in results if res["score"] >= similarity_threshold]
            
        logger.info(f"Retrieved {len(results)} chunks")
        return results
